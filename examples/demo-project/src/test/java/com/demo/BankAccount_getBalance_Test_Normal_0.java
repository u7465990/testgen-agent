package com.demo;

import org.junit.Test;
import static org.junit.Assert.assertEquals;
import com.demo.BankAccount;

public class BankAccount_getBalance_Test_Normal_0 {


    @Test
    public void testGetBalanceReturnsInitialBalance() {
        BankAccount account = new BankAccount("Alice", 1000.0);
        double result = account.getBalance();
        assertEquals(1000.0, result, 0.0001);
    }

}
