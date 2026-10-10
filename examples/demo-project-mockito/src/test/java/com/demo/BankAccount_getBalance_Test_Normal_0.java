package com.demo;

import com.demo.BankAccount;
import org.junit.Assert;
import org.junit.Test;

public class BankAccount_getBalance_Test_Normal_0 {


    @Test
    public void testGetBalanceReturnsInitialBalanceForTypicalAccount() {
        BankAccount account = new BankAccount("Alice", 100.0);

        double actual = account.getBalance();

        Assert.assertEquals(100.0, actual, 0.0);
    }

}
