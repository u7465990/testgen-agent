package com.demo;

import com.demo.BankAccount;
import org.junit.Assert;
import org.junit.Test;

public class BankAccount_getBalance_Test_Path_1 {


    @Test
    public void testGetBalanceReturnsInitialBalance() {
        BankAccount account = new BankAccount("Alice", 250.75);

        double result = account.getBalance();

        Assert.assertEquals(250.75, result, 0.0);
    }

}
