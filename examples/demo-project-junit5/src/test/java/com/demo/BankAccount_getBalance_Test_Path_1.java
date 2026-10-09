package com.demo;

import com.demo.BankAccount;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Assertions;

public class BankAccount_getBalance_Test_Path_1 {


    @Test
    public void testGetBalanceReturnsInitialBalance() {
        BankAccount account = new BankAccount("Alice", 100.0);
        double result = account.getBalance();
        Assertions.assertEquals(100.0, result, 0.0);
    }

}
